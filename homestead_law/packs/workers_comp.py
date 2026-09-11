"""The workers' comp pack — an active New Mexico claim (decision 7, wave 3).

A household member's WCA claim continues after the household's move to
Oregon: treatment moves, the forum does not. `JURISDICTION`/`JURISDICTIONS`
are both `"US-NM"` only — unlike custody (`US-NM` -> `US-OR`), this matter
never becomes an Oregon one; the one place the move enters the schema at all
is `oos_provider_affidavit_date`.

**The health boundary (decision 7).** *"Workers' comp is a law pack; medical
content stays in health."* Every field touching the claimant's medical facts
(`date_of_injury`, `body_part`, `diagnosis`, `impairment_rating`, `mmi_date`,
`treating_physician`, `ime`, `oos_provider_affidavit_date`) holds only a
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

**`ime` — one record per exam (decision 2), no bespoke writer.** `REPEATABLE`
addresses one exam per `--sub`, e.g. `put workers_comp ime "2026-10-05 -- Dr.
R. Chen -- no permanent restrictions" --id primary --sub 2026-10`. Date,
examiner and note all resolve to the claimant's medical evaluation, so the
field classifies once at its most protected fact's rung — the same reasoning
`immunizations.vaccine` gives for not splitting by sub-field name. The
existing generic `put`/`show` doors already carry a plain `L4` value through
`--id`/`--sub`; this bite adds no writer module (`doses.py`'s composed shape
is the general model decision 2 names, not a mandate here).

**`hcp_selection_date` reclassified `L1` (documented override).** The plan's
field list carries it at `L4`, among the medical-adjacent dates.
`L3-deadline-templates`' contract requires every `anchor` to render `L1`
(`compute()` reads it through the gate first), and the 60-day HCP-selection
window has no other candidate anchor. Reclassified here, on
`hcp_change_notice_date`'s footing: it records *when* a selection was made —
administrative, not the treatment relationship itself (`treating_physician`,
`L4`, is where that lives). Dropping the template instead (as
`notice_of_accident` is dropped, below) was rejected: unlike the 15-day
notice rule, this is the one deadline the claim actually needs tracked, and
its anchor is not itself the guarded medical fact.

**`notice_of_accident` — entered, not computed.** The 15-day rule (§ 52-1-29)
anchors on `date_of_injury` (`L4` — the medical fact this matter exists to
describe). Anchors must be `L1`, so no computed entry exists for it; a
household enters it directly, into `notes` or a `deadline` record.

**Both templates ship `UNCERTAIN`.** Both named sources were unreachable on
2026-09-11: `law.justia.com/.../section-52-1-49/` returned `EGRESS_BLOCKED`;
`wca.state.nm.us` failed DNS (`ETIMEOUT`). Three further tries — the
2025-edition Justia page, the official compiler `nmonesource.com`, and a
`web.archive.org` snapshot of the first — were each blocked the same way. A
general web search corroborates the 60-day figure in prose but is not a
dated, quoted fetch, so it does not carry a PROVENANCE this house style
accepts as `VERIFIED` — refuse to compute, never guess (I-2's rule, applied
to a counting rule instead of a date).
"""
from __future__ import annotations

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

#: One repeatable field: `ime` (decision 2). See the module docstring's "`ime`
#: — one composed record per exam" section for why no other field needs one.
REPEATABLE: frozenset[str] = frozenset({"ime"})


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
    "hcp_change_notice_date": _field(
        Rung.L1,
        "the date a change-of-provider notice was given — a procedural fact "
        "of the claim's own paperwork, not itself medical content (step 1: "
        "treated as public-in-this-forum the way a filed notice's timestamp "
        "is, so it can anchor a computed template, which reads only L1 "
        "anchors); step 3 no — a notice date carries no category. Added by "
        "this bite specifically because `hcp_change_objection`'s template "
        "needed an L1 anchor and the plan's own field list did not carry one.",
    ),
    "hcp_selection_date": _field(
        Rung.L1,
        "when the employer/insurer's initial health care provider selection "
        "was made — administrative (who chose, and when), not the clinical "
        "relationship itself (step 3 no: resolves to the claim's procedural "
        "posture, not a protected category). Reclassified from the plan's "
        "original L4 to L1 because it is the anchor the `hcp_selection` "
        "template reads (NMSA 1978 § 52-1-49(B)-(C)'s 60-day window), and an "
        "anchor must render at L1 — see the module docstring's own section "
        "on this override. The treating relationship this date sets in "
        "motion is still L4, via `treating_physician`.",
    ),
    "wca_case_number": _field(
        Rung.L3,
        "resolves to the claimant and the claim's parties (step 2 yes), no "
        "protected category by itself (step 3 no) — the model's own worked "
        "example, one case number sealed in a family matter and public in a "
        "bankruptcy; a WCA claim sits nearer the family posture than a "
        "bankruptcy's public docket, so L3, not L1.",
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
        "is L4 — the template cannot exist as computed (see the module "
        "docstring); this field is entered, never derived.",
        derived="A notice of accident date is on file",
    ),
    "hcp_change_objection_deadline": _field(
        Rung.L3,
        "the confirmed date, once known (from the WCA or counsel), that an "
        "objection to a health care provider change is due — resolves to "
        "the claim's procedural posture (step 2), no category (step 3 no). "
        "Distinct from TEMPLATES['hcp_change_objection'], an unverified "
        "computed *estimate* off hcp_change_notice_date (status UNCERTAIN) "
        "— this field is where the operator records the number once it is "
        "actually confirmed.",
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
    "treating_physician": _field(
        Rung.L4,
        "names a person providing medical care to the claimant — a "
        "treatment relationship is the protected category (step 3 yes), the "
        "same posture as custody's child_name naming a minor. The "
        "physician's clinical notes live in homestead-health; this field "
        "holds a short reference to who they are.",
        derived="A treating physician is named",
    ),
    "ime": _field(
        Rung.L4,
        "a repeatable field: one record per independent medical exam, "
        "addressed by --sub (decision 2). An exam's date, its examiner and "
        "any note about it all resolve to the claimant's medical evaluation "
        "(step 3 yes), so the field is classified once, at the rung its "
        "most protected fact requires — the same over-classify-rather-than-"
        "split-by-name reasoning custody.diagnosis and health's "
        "immunizations.vaccine already carry. The exam's clinical findings "
        "belong in homestead-health (decision 7); an ime entry here is a "
        "short reference (date, examiner, one-line note), never the "
        "underlying report, and validate_value/MAX_L4_CHARS is the "
        "structural nudge toward that until L4-surfaces wires it into the "
        "doors.",
        derived="An independent medical exam is on file",
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

    **Not yet called by any door** — `cli.py`'s `_cmd_put` and `server.py`'s
    `/api/store` both build a `Classified` straight from the pack's declared
    rung and store it, with no per-pack validation hook in between. Checked in
    `registry.py`/`cli.py` for an existing hook (`pack.validate`,
    `_validate_value`, anything similar) before writing this function: there
    is none. `L4-surfaces` (wave 4) is the bite named to wire it in; this one
    ships the function and the refusal shape only, per the bite's own scope
    (packs/workers_comp.py, a registry line, tests, docs — not the doors).

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


# ── deadline templates (item 3) — data only, read by the sibling rules.py ───
#
# TEMPLATES is data, not behaviour: it names an anchor field, a day count, a
# counting rule and a citation, and the counting itself is the parallel
# L3-deadline-templates bite's job (`homestead_law.rules`, not imported here —
# these two bites run side by side and neither depends on the other's module).

#: The closed set `direction` may take.
TEMPLATE_DIRECTIONS = frozenset({"forward", "backward"})
#: The closed set `rule` may take — the four counting rules the engine's
#: `homestead.keep.dates` (or its wrapper) is expected to support (decision 4).
TEMPLATE_RULES = frozenset({"court_days", "court_days_before", "business_days", "calendar_days"})
#: The closed set `status` may take. UNCERTAIN refuses to compute; VERIFIED
#: requires a dated PROVENANCE from a reachable secondary source (I-2's rule,
#: applied to a counting rule instead of a date).
TEMPLATE_STATUSES = frozenset({"VERIFIED", "UNCERTAIN"})

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


#: Two candidate deadline templates. `notice_of_accident` (15 days from
#: date_of_injury, § 52-1-29) is deliberately absent — see the module
#: docstring's "notice_of_accident — entered, not computed" section; its
#: anchor is L4 and a computed template's anchor must be L1.
TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "name": "hcp_selection",
        "anchor": "hcp_selection_date",
        "days": 60,
        "direction": "forward",
        "rule": "calendar_days",
        "mail": False,
        "jurisdiction": "US-NM",
        "source": (
            "NMSA 1978 § 52-1-49(B)-(C): the party that did not make the "
            "initial selection may change the health care provider after 60 "
            "days; confirm with the WCA"
        ),
        "status": "UNCERTAIN",
        "note": (
            "No PROVENANCE: law.justia.com's 2021 and 2025 chapter-52 pages, "
            "nmonesource.com (the official compiler) and web.archive.org's "
            "snapshot of the first were each unreachable from this "
            "environment on 2026-09-11 (EGRESS_BLOCKED, DNS timeout, or the "
            "fetch tool's own refusal). A general web search corroborates "
            "the 60-day figure in prose but is not a dated, quoted fetch of "
            "the statute, so this ships UNCERTAIN until a builder with reach "
            "can quote it directly."
        ),
    },
    {
        "name": "hcp_change_objection",
        "anchor": "hcp_change_notice_date",
        "days": 3,
        "direction": "forward",
        "rule": "calendar_days",
        "mail": False,
        "jurisdiction": "US-NM",
        "source": (
            "NMSA 1978 § 52-1-49 area — an objection window to a change of "
            "health care provider; the counting rule itself (forward vs. "
            "backward, calendar vs. business days, any mail allowance) is "
            "not verified from here"
        ),
        "status": "UNCERTAIN",
        "note": (
            "direction/rule above are placeholders only, present to satisfy "
            "the shape check — status UNCERTAIN refuses computation "
            "regardless of what they say, so they must not be read as "
            "verified values by any caller."
        ),
    },
)

_validate_templates(TEMPLATES, SCHEMA, FIELDS, JURISDICTIONS)
