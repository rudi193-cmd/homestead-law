"""The workers' comp pack — an active New Mexico claim (decision 7, wave 3).

A household member's WCA claim continues after the household's move to
Oregon: treatment moves, the forum does not. `JURISDICTION`/`JURISDICTIONS`
are both `"US-NM"` only — unlike custody (`US-NM` -> `US-OR`), this matter
never becomes an Oregon one; the one place the move enters the schema at all
is `oos_provider_affidavit_date`.

**The health boundary (decision 7).** *"Workers' comp is a law pack; medical
content stays in health."* Every field touching the claimant's medical facts
(`date_of_injury`, `body_part`, `diagnosis`, `impairment_rating`, `mmi_date`,
`treating_physician`, `hcp_selection_date`, `ime.*`,
`oos_provider_affidavit_date`) holds only a
**date or a short reference** — never the exam note or the treatment
narrative, which belong in `homestead-health`'s own packs (see
`homestead_health/packs/immunizations.py`'s `vaccine`/`notes` split for the
shape). `MAX_L4_CHARS`/`validate_value` below are the structural fence: a
value over the cap on an `L4` field is refused by field name, without
echoing what was typed (I-15). **Not yet called by any door** — `cli.py` and
`server.py` were checked for an existing validation hook before writing this
function; none exists. `L4-surfaces` (wave 4) is the bite that wires it in;
`tests/test_workers_comp.py` documents the gap so it is not forgotten.

**Financial, not medical** (`aww`, `benefit_rate`, `tt_benefit_start`): kept
at `L4` on the ledger's own account-balance reasoning — a precise wage figure
is sensitive once paired with a public-adjacent claim record, the same
argue-up posture custody's `notes` gives for behavioral content, applied to
income precision rather than a protected category. `tt_benefit_start` is a
bare date kept beside them rather than argued down, because it ties a date to
the claimant's medical incapacity to work (over-classify, not a guess).

**`ime.date` / `ime.examiner` / `ime.note` — three dotted sub-fields, one
independent medical exam per `--sub` (decision 2).** `REPEATABLE` names the
three dotted fields, not the bare word `ime`, because that is the only shape
this module's own write door can drive: `cli._cmd_put` checks `field not in
mt.repeatable` against the *exact* string the operator typed, and
`registry._validate`'s `unknown_repeatable` guard checks each `REPEATABLE`
member against `FIELDS`, so a bare `"ime"` entry needs a bare `"ime"` field in
`SCHEMA` and there is no CLI syntax that composes three arguments into one
record (`homestead_health.doses.add_dose` does that from a *Python* caller,
not from a door). `put workers_comp ime.date 2026-10-05 --id primary --sub
2026-10`, then `ime.examiner` and `ime.note` under the same `--sub`.
`homestead_law.packs.custody` reached the identical conclusion for
`child.name`/`child.dob`/`child.school` (struck 2026-09-11 in its own
docstring); the two packs use one convention deliberately — ~~a single `ime`
field carrying `"date -- examiner -- note"` as one string~~ was this bite's
first shape and is struck: it made `ime` a *second* free-text field beside
`notes`, which is exactly the drift toward narrative decision 7 and
`MAX_L4_CHARS` exist to stop, and it spent one 200-character budget on three
facts instead of three. All three sit at `L4`: splitting by name changes the
*shape*, never the rung, and each one resolves to the claimant's medical
evaluation on its own.

**`hcp_selection_date` stays `L4`, and its 60-day window is entered, not
computed (audit ruling, 2026-09-11).** ~~Reclassified from the plan's `L4` to
`L1` so the 60-day template would have an anchor.~~ Struck. Running the five
steps on the *harm of disclosure*, which is the only thing they answer:

* **Step 1 — public in this matter's forum?** No. This pack has already ruled
  that its forum does not post: `wca_case_number` is `L3` because "a WCA claim
  sits nearer the family posture than a bankruptcy's public docket", and
  `hearing_date`/`mediation_date` are `L3` because a WCA calendar "is not
  treated as posted-public from here". A provider-selection date is less
  public than either. Step 1 cannot answer yes for this field while answering
  no for the hearing it schedules.
* **Step 2 — resolves to a person?** Yes, to the claimant. So at least `L3`.
* **Step 3 — a category the law follows?** Yes: the date states that a *health
  care provider* was chosen for an identified person and when their treatment
  was organised. That is a health-care fact about an identified individual —
  the same thing `oos_provider_affidavit_date` is `L4` for one field below
  ("the date resolves to an active treatment relationship"), and the same
  over-classify default `tt_benefit_start` and `mmi_date` already take for a
  bare date. `treating_physician` holding the *name* does not make the date
  administrative; both are facts about one treatment relationship.
* **Step 4 — key material, refusal, privilege, sealing order?** No. `L4`.
* **Step 5 — recorded with matter and jurisdiction**, as every `_field` here is.

So the honest rung is `L4`, and it is the template that goes, not the rung: a
computed template's anchor must render `L1` because `compute()` reads it
through the gate on `S1_LIST` before any arithmetic, and an `L4` value
`DERIVE`s there — `compute()` could not read this date even if the contract
allowed it. ~~`hcp_change_notice_date`, an `L1` field added by this bite to
anchor the second template~~ is struck for the same reason and is gone: it
existed only to be an anchor, it would have taken `L4` on this identical
analysis, and `hcp_change_objection_deadline` (`L3`) already records the
objection date once the WCA or counsel confirms it.

**Nothing in this pack is a computed template; `TEMPLATES` is empty.** All
three candidate NM rules anchor above `L1`:

* the 60-day HCP-change window (NMSA 1978 § 52-1-49(B)-(C)) on
  `hcp_selection_date` (`L4`, above);
* the 3-day objection window to a provider change, on a notice date that is
  `L4` by the same analysis;
* the 15-day notice-of-accident rule (§ 52-1-29) on `date_of_injury` (`L4` —
  the medical fact this matter exists to describe).

Each is entered by the household — `hcp_change_objection_deadline`,
`notice_of_accident_date` and the `deadline` record `cli.deadline` already
writes — never derived here. The citations stay on the fields' own `why`
strings so the reference is not lost with the arithmetic.

**And the counting rules were never verified anyway.** Every named source was
unreachable on 2026-09-11: `law.justia.com/.../section-52-1-49/` returned
`EGRESS_BLOCKED`; `wca.state.nm.us` failed DNS (`ETIMEOUT`); the 2025-edition
Justia page, the official compiler `nmonesource.com` and a `web.archive.org`
snapshot of the first were each blocked the same way. A general web search
corroborates the 60-day figure in prose but is not a dated, quoted fetch, so
it carries no PROVENANCE this house style accepts as `VERIFIED`. Even with an
`L1` anchor these would have shipped `UNCERTAIN` and refused to compute
(I-2's rule, applied to a counting rule instead of a date) — the rung ruling
above is what removes them, and the missing provenance is why nothing is lost
by it.
"""
from __future__ import annotations

import re
from typing import Any

from homestead.keep.rungs import Rung, classify_schema

__all__ = [
    "MATTER", "JURISDICTION", "JURISDICTIONS", "REPEATABLE", "SCHEMA", "FIELDS",
    "MAX_L4_CHARS", "MedicalNarrativeTooLong", "validate_value",
    "TEMPLATE_DIRECTIONS", "TEMPLATE_RULES", "TEMPLATE_STATUSES",
    "TemplateShapeError", "TEMPLATES",
]

MATTER = "workers_comp"
JURISDICTION = "US-NM"
#: A single-member tuple, deliberately. This household's WCA claim does not
#: move with the household the way the custody order does (decision 1's own
#: contrast): New Mexico governs an injury that happened under New Mexico's
#: workers' compensation law regardless of where the claimant now lives or is
#: treated. Nothing here tracks a second jurisdiction because there is not one.
JURISDICTIONS: tuple[str, ...] = ("US-NM",)

#: The dotted sub-fields that may carry a sub-id (`homestead_law.instances`,
#: decision 2) — one independent medical exam per `--sub`. Three field names,
#: not the bare word `"ime"`: `cli._cmd_put` and `registry._validate`'s
#: `unknown_repeatable` guard both hold a `REPEATABLE` member against the
#: literal field string, and nothing here declares a bare `"ime"`. The same
#: convention `homestead_law.packs.custody` uses for `child.*`; see the module
#: docstring for why the two packs converged on it.
REPEATABLE: frozenset[str] = frozenset({"ime.date", "ime.examiner", "ime.note"})


def _field(rung: Rung, why: str, *, derived: str | None = None) -> dict[str, Any]:
    decl = {"rung": rung, "matter": MATTER, "jurisdiction": JURISDICTION, "why": why}
    if derived is not None:
        decl["derived"] = derived
    return decl


#: The closed workers'-comp schema. Field -> declaration (rung + matter +
#: jurisdiction + reason), the same shape `homestead_law.packs.custody` uses.
#: Nothing here is keyed on a field name; every rung is a property of the
#: field *in this matter and jurisdiction* (step 5).
SCHEMA: dict[str, dict[str, Any]] = {
    "jurisdiction": _field(
        Rung.L1,
        "the forum's identity is public in this matter's forum (step 1); the "
        "value is one of JURISDICTIONS and is read by deadline arithmetic "
        "(decision 1).",
    ),
    "wca_case_number": _field(
        Rung.L3,
        "resolves to the claimant and the claim's parties (step 2 yes), no "
        "protected category by itself (step 3 no) — the model's own worked "
        "example, one case number sealed in a family matter and public in a "
        "bankruptcy; a WCA claim sits nearer the family posture than a "
        "bankruptcy's public docket, so L3, not L1. Not L4 either (audit, "
        "2026-09-11): a docket number takes its rung from how public its "
        "forum is, not from what the matter is about — the model puts a "
        "bankruptcy case number at L1 even though insolvency is a category "
        "the law follows — and the derived form on a list says only what the "
        "matter name already says.",
        derived="A WCA case number is on file",
    ),
    "claim_number": _field(
        Rung.L3,
        "same posture as the WCA case number — an insurer-issued reference "
        "that resolves to the claim's parties (step 2), carrying no category "
        "of its own (step 3 no).",
        derived="A claim number is on file",
    ),
    "employer": _field(
        Rung.L3,
        "names a party to the claim — the employer — resolving to the "
        "claimant's workplace and household (step 2 yes); no protected "
        "category is carried by a business name alone (step 3 no).",
        derived="An employer is named in this matter",
    ),
    "insurer": _field(
        Rung.L3,
        "names the insurer administering the claim — a party, resolving to "
        "the claim (step 2), no category of its own (step 3 no).",
        derived="An insurer is named in this matter",
    ),
    "adjuster": _field(
        Rung.L3,
        "names a person handling the claim on the insurer's behalf — "
        "resolves to the claim and to that individual (step 2), no "
        "protected category attached (step 3 no).",
        derived="A claims adjuster is named in this matter",
    ),
    "notice_of_accident_date": _field(
        Rung.L3,
        "when the accident was reported — resolves to the claim's timeline "
        "and the claimant (step 2), no category by itself (step 3 no). Not "
        "an anchor for a computed template: the 15-day notice window (§ "
        "52-1-29) would need `date_of_injury` as its anchor, and that field "
        "is L4, while a computed template may only anchor on an L1 field "
        "(see the module docstring); this field is entered, never derived.",
        derived="A notice of accident date is on file",
    ),
    "hcp_change_objection_deadline": _field(
        Rung.L3,
        "the confirmed date, once known (from the WCA or counsel), that an "
        "objection to a health care provider change is due — resolves to "
        "the claim's procedural posture (step 2), no category (step 3 no). "
        "Entered, never computed: the objection window's own anchor (the "
        "date the change notice was given) is an L4 health-care fact and a "
        "computed template may only anchor on L1, and the counting rule "
        "itself — 3 days, calendar or working — was never verifiable from "
        "here (see the module docstring). This field is where the operator "
        "records the date once it is actually confirmed.",
        derived="A health care provider change objection deadline is on file",
    ),
    "mediation_date": _field(
        Rung.L3,
        "a scheduled mediation session — resolves to the claim and its "
        "parties (step 2); unlike a district court's public calendar, a WCA "
        "mediation date is not treated as posted-public from here (step 1 "
        "no), and carries no category of its own (step 3 no).",
        derived="A mediation date is on file",
    ),
    "hearing_date": _field(
        Rung.L3,
        "a scheduled WCA hearing — same posture as mediation_date: resolves "
        "to the claim's parties (step 2), not treated as a posted public "
        "calendar from this pack (step 1 no, unlike custody's district-court "
        "hearing_date), no category (step 3 no).",
        derived="A hearing date is on file",
    ),
    "complaint_date": _field(
        Rung.L3,
        "when a formal complaint was filed with the WCA — resolves to the "
        "claim and its parties (step 2), no category of its own (step 3 no).",
        derived="A complaint date is on file",
    ),
    "date_of_injury": _field(
        Rung.L4,
        "the date of the injury resolves to the claimant's medical event "
        "(step 2 yes) and, with the claim, carries a protected category — an "
        "injury is the medical fact this whole matter exists to describe "
        "(step 3 yes). The clinical narrative of what happened belongs in "
        "homestead-health (decision 7); this field holds only the date, and "
        "its derived form withholds even the year, since a bare year beside "
        "an employer/insurer would itself narrow when in the claimant's "
        "life the injury happened.",
        derived="A date of injury is on file",
    ),
    "body_part": _field(
        Rung.L4,
        "names the injured body part attached to the claimant — a medical "
        "category by itself (step 3 yes). The clinical detail — imaging, "
        "exam findings, treatment notes — lives in homestead-health "
        "(decision 7); this field holds only the short administrative "
        "reference a WC claim carries, length-capped by validate_value "
        "against drifting into narrative.",
        derived="An injured body part is on file",
    ),
    "diagnosis": _field(
        Rung.L4,
        "a medical category attached to a person (step 3 yes), the same "
        "posture as custody's diagnosis. The clinical substance belongs in "
        "homestead-health (decision 7); this field is a short reference "
        "only, length-capped by validate_value.",
        derived="A medical diagnosis is on file",
    ),
    "impairment_rating": _field(
        Rung.L4,
        "a percentage tied to the claimant's medical condition (step 3 yes) "
        "— reveals the severity of a protected medical category even as a "
        "bare number. Its clinical basis lives in homestead-health; this "
        "field holds only the number the WC claim tracks.",
        derived="An impairment rating is on file",
    ),
    "mmi_date": _field(
        Rung.L4,
        "maximum medical improvement is a medical determination about the "
        "claimant's condition (step 3 yes) — the date alone states where "
        "the claimant's recovery has plateaued. The clinical basis lives in "
        "homestead-health (decision 7); this field holds only the date.",
        derived="A maximum medical improvement date is on file",
    ),
    "hcp_selection_date": _field(
        Rung.L4,
        "when the initial health care provider selection was made under NMSA "
        "1978 § 52-1-49(B)-(C) — a date that states a health care provider "
        "was chosen for this claimant and when their treatment was organised. "
        "Step 1 no: this pack's forum does not post (see wca_case_number and "
        "hearing_date). Step 2 yes, to the claimant. Step 3 yes: a "
        "health-care fact about an identified person, the same posture "
        "oos_provider_affidavit_date and treating_physician already hold, and "
        "the over-classify default mmi_date and tt_benefit_start take for a "
        "bare date. Only the date is here: who the provider is and what "
        "they treat live in treating_physician and in homestead-health "
        "(decision 7). ~~L1, so the 60-day window could be a computed "
        "template~~ — struck 2026-09-11 by audit: the rung answers the harm "
        "of disclosure, not what a template needs, so the template went (see "
        "the module docstring). The 60-day window is still the figure to "
        "confirm with the WCA; it is entered, never derived here.",
        derived="A health care provider selection date is on file",
    ),
    "treating_physician": _field(
        Rung.L4,
        "names a person providing medical care to the claimant — a "
        "treatment relationship is the protected category (step 3 yes), the "
        "same posture as custody's child.name naming a minor (that pack's "
        "singular ~~child_name~~ was retired 2026-09-11 by L9-child-name; "
        "the posture this sentence borrows is unchanged, only its name). "
        "The "
        "physician's clinical notes live in homestead-health; this field "
        "holds a short reference to who they are.",
        derived="A treating physician is named",
    ),
    "ime.date": _field(
        Rung.L4,
        "the date of one independent medical exam, addressed by --sub "
        "(decision 2, one exam per sub-id). Resolves to the claimant (step 2) "
        "and states that a medical evaluation of this person happened on that "
        "day — a health-care fact about an identified person (step 3 yes), "
        "the same posture mmi_date holds for a bare date. Declared per "
        "sub-field, not as one `ime` blob, so a second exam does not overwrite "
        "the first and no one field has to hold a whole exam; the convention "
        "custody's child.name/child.dob/child.school also uses. The exam's "
        "findings belong in homestead-health (decision 7); only the date is "
        "here.",
        derived="An independent medical exam date is on file",
    ),
    "ime.examiner": _field(
        Rung.L4,
        "names the physician who performed that exam — a person providing a "
        "medical evaluation of the claimant (step 2 yes, step 3 yes), the "
        "same posture as treating_physician. A short reference to who they "
        "are; the exam's findings belong in homestead-health (decision 7).",
        derived="An independent medical examiner is named",
    ),
    "ime.note": _field(
        Rung.L4,
        "one line about that exam — an appointment kept, a report received, a "
        "restriction the operator wants beside the date. Resolves to the "
        "claimant and routinely carries the medical category the exam is "
        "about (step 3 yes). The exam report itself belongs in "
        "homestead-health (decision 7); MAX_L4_CHARS/validate_value is the "
        "structural fence keeping this a reference rather than a narrative, "
        "and it is one budget per exam rather than one shared with the date "
        "and the examiner.",
        derived="A note about an independent medical exam is on file",
    ),
    "aww": _field(
        Rung.L4,
        "the average weekly wage is an exact income figure that resolves to "
        "the household's finances (step 2 yes); a precise wage figure is "
        "itself sensitive content once paired with a public-adjacent claim "
        "record, so it is kept at the ledger's own L4 posture for an "
        "account balance rather than L3 — not medical, but the same "
        "argue-up reasoning custody's notes carries for behavioral content "
        "(step 3's spirit, applied to income precision).",
        derived="An average weekly wage figure is on file",
    ),
    "benefit_rate": _field(
        Rung.L4,
        "the weekly benefit amount, computed from aww — the same "
        "exact-income posture as aww (step 2 yes), kept beside it at L4 "
        "rather than split across rungs, since the two numbers reveal each "
        "other.",
        derived="A benefit rate is on file",
    ),
    "tt_benefit_start": _field(
        Rung.L4,
        "when temporary total disability benefits began — ties a specific "
        "date to the claimant's medical incapacity to work (step 3 yes, the "
        "same posture as mmi_date), even though the date alone carries no "
        "clinical content; kept at L4 rather than argued down, the model's "
        "over-classify default, not a guess.",
        derived="A temporary total benefit start date is on file",
    ),
    "oos_provider_affidavit_date": _field(
        Rung.L4,
        "the date an out-of-state provider affidavit was filed (§ 52-4-1 "
        "NMSA; 11.4.7.10 NMAC) — the affidavit exists because the claimant "
        "is being treated by a provider outside New Mexico, so the date "
        "resolves to an active treatment relationship the household took up "
        "after the move (step 3 yes, the same posture as treating_physician). "
        "The affidavit's clinical content lives in homestead-health; this "
        "field holds only the date it was filed.",
        derived="An out-of-state provider affidavit date is on file",
    ),
    "notes": _field(
        Rung.L4,
        "free operator text that resolves to the claimant (step 2) and "
        "routinely carries a protected medical or financial category — an "
        "examiner's remark, a settlement figure, an allegation about the "
        "adjuster (step 3 yes). Kept at L4 on the same reasoning "
        "custody.notes states (2026-08-10): a note never reaches a model "
        "prompt (S2, ceiling L2 -> derived) or an agent (I-15), and the "
        "operator reads their own note in the detail pane. Any clinical "
        "narrative that belongs in homestead-health should be entered "
        "there, not copied here; validate_value/MAX_L4_CHARS is the "
        "structural nudge toward a reference rather than a narrative, not "
        "yet wired into either door.",
        derived="An operator note is on file",
    ),
    "ssn": _field(
        Rung.L5,
        "key material — sealed, and L5 has no override anywhere (step 4). "
        "The corpus's canonical L5 datum; served on no surface, in any "
        "form.",
    ),
}

#: Classified at import (I-11). This line is the build failure: remove any
#: field's rung above and the process defining the schema dies, naming it.
FIELDS: dict[str, Rung] = classify_schema(SCHEMA)


# ── the L4 length cap (item 2: medical narrative belongs in health) ─────────

#: A pack-level cap on how long an L4 value may be. Not itself an engine
#: constant — every pack that wants one declares its own (I-11: absence never
#: defaults). 200 is generous for a body part, an examiner's name, a rating
#: number or a one-line note, and inhospitable to a clinical paragraph.
MAX_L4_CHARS = 200


class MedicalNarrativeTooLong(ValueError):
    """An L4 value longer than MAX_L4_CHARS — refused by field name, never by
    echoing what was typed (I-15). `validate_value` is the only place that
    raises this; see the module docstring's note that no door calls it yet."""

    def __init__(self, field: str) -> None:
        super().__init__(
            f"{field}: refused — an L4 value here is longer than "
            f"{MAX_L4_CHARS} characters. Medical narrative belongs in "
            "homestead-health (decision 7); this field holds a date or a "
            "short reference, not a clinical note. This refusal does not "
            "repeat what was typed (I-15)."
        )
        self.field = field


def validate_value(field: str, value: object) -> None:
    """Refuse an L4 value over MAX_L4_CHARS; silent for every other field and
    every other rung.

    ~~**Not yet called by any door** — `cli.py`'s `_cmd_put` and `server.py`'s
    `/api/store` both build a `Classified` straight from the pack's declared
    rung and store it, with no per-pack validation hook in between. …
    `L4-surfaces` (wave 4) is the bite named to wire it in.~~ Struck
    (L4-surfaces, 2026-09-11): **both writing doors now call this** before
    building the `Classified` they would store — `cli._cmd_put` and
    `server._post_store`, each guarded by `hasattr(mt.pack,
    "validate_value")` so a pack that declares none pays nothing.
    `tests/test_workers_comp.py::test_the_doors_call_validate_value` was the
    `xfail(strict=True)` claim that flipped when it landed.

    A caller that does reach for this directly — this pack's own tests, or a
    future door — gets I-11's shape: absence of a check is not the same as
    permission, and the check is here the moment anything wants it.
    """
    if not isinstance(field, str) or field not in FIELDS:
        return
    if FIELDS[field] is not Rung.L4:
        return
    if not isinstance(value, str):
        return
    if len(value) > MAX_L4_CHARS:
        raise MedicalNarrativeTooLong(field)


# ── deadline templates — empty here, and the shape check that keeps it honest ─
#
# A template is data, not behaviour: an anchor field, a day count, a counting
# rule and a citation, read by `homestead_law.rules` (never imported here —
# that module is the one place a date is counted). This pack declares none:
# all three New Mexico rules it carries anchor on a field it declares `L4`,
# and a computed template may only anchor on `L1` (see the module docstring's
# ruling). The check below still runs at import, so the day a template *is*
# added it is held to the shape and to the anchor rule by the build, and
# `rules.validate_templates` holds it again at registry time once that bite
# lands.

#: The closed set `direction` may take.
TEMPLATE_DIRECTIONS = frozenset({"forward", "backward"})
#: The closed set `rule` may take — the four counting rules the engine's
#: `homestead.keep.dates` (or its wrapper) is expected to support (decision 4).
TEMPLATE_RULES = frozenset({"court_days", "court_days_before", "business_days", "calendar_days"})
#: The closed set `status` may take. UNCERTAIN refuses to compute; VERIFIED
#: requires a dated PROVENANCE from a reachable secondary source (I-2's rule,
#: applied to a counting rule instead of a date).
TEMPLATE_STATUSES = frozenset({"VERIFIED", "UNCERTAIN"})

#: An id, by `homestead_law.instances.ID_PATTERN`'s own rule (decision 2) —
#: copied rather than imported so a pack stays a leaf that imports only the
#: engine's `rungs`, with `tests/test_workers_comp.py` asserting the two
#: patterns have not drifted. A template's `name` becomes the `<sub>` half of
#: the `"<instance>.<template>"` item_id an accepted deadline is stored under,
#: so a name with an underscore in it could never be written back.
_TEMPLATE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")

#: A template's required keys — the shape `_validate_templates` checks below.
_TEMPLATE_KEYS = frozenset(
    {"name", "anchor", "days", "direction", "rule", "mail", "jurisdiction", "source", "status", "note"}
)


class TemplateShapeError(ValueError):
    """A `TEMPLATES` entry that does not match the closed shape, or whose
    `anchor` is not a field this pack declares at `L1`. Raised at import (the
    call at the bottom of this section), the same build-failure posture
    `classify_schema` gives an unclassified field (I-11)."""


def _validate_templates(
    templates: tuple[dict[str, Any], ...],
    schema: dict[str, dict[str, Any]],
    fields: dict[str, Rung],
    jurisdictions: tuple[str, ...],
) -> None:
    """Pure in its four arguments (`registry._validate`'s own shape), so a
    broken template can be fired against this function directly in a test
    rather than only asserted to be caught."""
    for entry in templates:
        name = entry.get("name") if isinstance(entry, dict) else None
        label = name if isinstance(name, str) and name else "<unnamed template>"

        if not isinstance(entry, dict):
            raise TemplateShapeError(f"{label}: a template must be a dict, not {type(entry).__name__}")

        missing = sorted(_TEMPLATE_KEYS - set(entry))
        extra = sorted(set(entry) - _TEMPLATE_KEYS)
        if missing or extra:
            raise TemplateShapeError(
                f"{label}: keys {sorted(entry)} do not match the required shape "
                f"{sorted(_TEMPLATE_KEYS)} — missing {missing}, unexpected {extra}"
            )

        if not isinstance(entry["name"], str) or not entry["name"].strip():
            raise TemplateShapeError(f"{label}: 'name' must be a non-empty string")
        if not _TEMPLATE_NAME.match(entry["name"]):
            raise TemplateShapeError(
                f"{label}: a template name is stored as a repeatable sub-id "
                f"(the `<instance>.<template>` item_id an accepted deadline "
                f"takes), so it must match {_TEMPLATE_NAME.pattern} — no "
                "underscore, no dot, no capital."
            )

        anchor = entry["anchor"]
        if not isinstance(anchor, str) or anchor not in fields:
            raise TemplateShapeError(
                f"{label}: anchor {anchor!r} is not a field this pack declares"
            )
        if fields[anchor] is not Rung.L1:
            raise TemplateShapeError(
                f"{label}: anchor {anchor!r} is {fields[anchor].value}, not L1 — "
                "a computed template's anchor must render at L1, because "
                "compute() reads it through the gate before any arithmetic runs "
                "(L3-deadline-templates' own contract). A higher-rung field "
                "cannot be a computed anchor; enter that deadline instead."
            )

        days = entry["days"]
        if not isinstance(days, int) or isinstance(days, bool) or days <= 0:
            raise TemplateShapeError(f"{label}: 'days' must be a positive int, not {days!r}")

        if entry["direction"] not in TEMPLATE_DIRECTIONS:
            raise TemplateShapeError(
                f"{label}: 'direction' {entry['direction']!r} not in {sorted(TEMPLATE_DIRECTIONS)}"
            )
        if entry["rule"] not in TEMPLATE_RULES:
            raise TemplateShapeError(
                f"{label}: 'rule' {entry['rule']!r} not in {sorted(TEMPLATE_RULES)}"
            )
        if not isinstance(entry["mail"], bool):
            raise TemplateShapeError(f"{label}: 'mail' must be a bool, not {entry['mail']!r}")

        jurisdiction = entry["jurisdiction"]
        if jurisdiction is not None and jurisdiction not in jurisdictions:
            raise TemplateShapeError(
                f"{label}: 'jurisdiction' {jurisdiction!r} is neither None nor "
                f"a member of {jurisdictions}"
            )
        if not isinstance(entry["source"], str) or not entry["source"].strip():
            raise TemplateShapeError(f"{label}: 'source' must be a non-empty string")
        if entry["status"] not in TEMPLATE_STATUSES:
            raise TemplateShapeError(
                f"{label}: 'status' {entry['status']!r} not in {sorted(TEMPLATE_STATUSES)}"
            )
        if not isinstance(entry["note"], str) or not entry["note"].strip():
            raise TemplateShapeError(f"{label}: 'note' must be a non-empty string")


#: Empty, and the module docstring says why at length: all three candidate NM
#: rules (the 60-day HCP-change window, the 3-day objection window, the 15-day
#: notice of accident) anchor on a field this pack declares at `L4`, and a
#: computed template may only anchor on `L1` — `compute()` reads the anchor
#: through the gate on `S1_LIST`, where an `L4` value renders as its derived
#: form and no date reaches the arithmetic at all. Each of the three is
#: entered by the household instead; the citations stay on the anchoring
#: fields' own `why` strings. An empty tuple is not an omission: a pack that
#: declares no template is the ordinary case (`custody` shipped that way), and
#: `_validate_templates` below still runs, so the day anything is added here
#: it is held to the shape and to the `L1` anchor rule at import.
TEMPLATES: tuple[dict[str, Any], ...] = ()

_validate_templates(TEMPLATES, SCHEMA, FIELDS, JURISDICTIONS)
