"""Bite 2 of docs/PLAN-first-runnable.md — the custody pack, and
`classify_schema` called for the first time.

Phase 2 built the refusal and tested it hard, but against synthetic schemas: the
exit criterion *"an unclassified field fails the build"* was, in the words of
`DECISION-unclassified-field-instrument.md`, *"a lock on an empty room."* This is
the room getting something in it — the first real schema in the package, a
custody matter (this household's is US-NM, being registered in US-OR — wave 2's
"L2a-pack-contract" bite), classified at **import** so an unclassified field
stops the build rather than surprising someone at runtime.

Packs are fixed: the operator-extends-a-pack question (P-3, Option A) is answered
*no* for v1, so a pack is a closed schema authored by the project, and the only
way a field goes unclassified is an author's omission — which is exactly what
import-time classification catches.

The rungs here are the model's own worked examples, not this file's invention: a
case number is `L3` in a *custody* matter (family records are commonly sealed)
where it is `L1` in a bankruptcy, an SSN is `L5`, a minor's name and schedule are
`L4`. `docs/homestead-rungs.md` § "Classifying a new field" and the surfaces
corpus are the provenance.
"""
from __future__ import annotations

import copy

import pytest

from homestead.keep.rungs import Rung, classify_schema
from homestead_law.packs import custody


def test_the_pack_classifies_at_import():
    """Importing the module already ran the classifier — `FIELDS` exists because
    `classify_schema(SCHEMA)` ran at module top level. A pack that deferred
    classification to a caller would move the build failure to runtime, which is
    the whole thing this bite exists to prevent."""
    assert isinstance(custody.FIELDS, dict)
    assert custody.FIELDS
    assert all(isinstance(r, Rung) for r in custody.FIELDS.values())
    assert set(custody.FIELDS) == set(custody.SCHEMA)


def test_the_pack_spans_the_ladder_with_defensible_rungs():
    """The reference pack, field by field, against homestead-rungs.md § Custody.

    The rungs that appear in the doc's reference table match it exactly rather
    than raising above it: the audit caught two fields (hearing_date,
    parenting_time) classified *higher* than the doc with a citation that claimed
    the doc as authority — an over-classification is safe but a false provenance
    is not, so both were aligned to the table (hearing date L1, parenting
    schedule L3) and the reasons corrected. Over-classifying is not free: a
    hearing date at L2 would not reach the local model a publicly-posted date may,
    and a parenting schedule at L4 would be withheld from the operator's own list
    where the doc says they should see it."""
    expected = {
        "courthouse": Rung.L1,       # the court's public identity
        "hearing_date": Rung.L1,     # posted on the court calendar (doc § Custody: L1)
        "jurisdiction": Rung.L1,     # the forum's identity — public in this matter's forum
        "case_number": Rung.L3,      # family records commonly sealed (the worked example)
        "docket": Rung.L3,           # same posture as a case number in a family matter
        "opposing_party": Rung.L3,   # names a person; no protected category
        "parenting_time": Rung.L3,   # resolves to the child (doc § Custody: L3)
        "child_name": Rung.L4,       # names a person who is a minor — a category the law follows
        "diagnosis": Rung.L4,        # a medical category attached to a person
        "notes": Rung.L4,            # free operator text; routinely carries a protected category (F-4)
        "ssn": Rung.L5,              # sealed / key material — L5 has no override
        # ── L3-custody-relocation (wave 3) ──────────────────────────────────
        "custody_order_date": Rung.L1,          # a fact of the court record
        "uccjea_registration_date": Rung.L1,    # a fact of the receiving forum's record
        "registration_contest_deadline": Rung.L1,  # posted on the court calendar
        "mediation_date": Rung.L1,              # posted on the court calendar
        "new_residence_state": Rung.L2,         # a household-level fact, no identity
        "custody_type": Rung.L3,                # resolves to the family's arrangement
        "move_date": Rung.L3,                   # resolves to the family's whereabouts
        "relocation_notice_date": Rung.L3,      # resolves to the other parent
        "child.name": Rung.L4,                  # a minor's name, per child (repeatable)
        "child.dob": Rung.L4,                   # a minor's date of birth, per child
        "child.school": Rung.L4,                # a minor's school, per child
    }
    assert custody.FIELDS == expected


def test_the_dangerous_rungs_are_where_they_must_be():
    """Spot-checks that would be catastrophic to get wrong, stated on their own
    so a change to them fails by name."""
    assert custody.FIELDS["ssn"] is Rung.L5, "an SSN is L5 — L5 has no override"
    assert custody.FIELDS["child_name"] is Rung.L4, "a minor's name identifies a minor"
    assert custody.FIELDS["diagnosis"] is Rung.L4, "a diagnosis is a category the law follows"


def test_every_field_records_matter_and_jurisdiction():
    """Step 5 of the classification procedure: the rung is recorded *with* the
    matter type and the jurisdiction, because step 1 (is it public in this
    matter's forum?) depends on both and neither is derivable from the field
    name. A pack that dropped them would be un-reviewable — nobody could check a
    rung without knowing the forum it was set in."""
    for name, spec in custody.SCHEMA.items():
        assert spec.get("matter") == "custody", name
        assert spec.get("jurisdiction"), name
        assert spec.get("why"), f"{name} declares a rung with no recorded reason"


def test_deleting_a_fields_rung_fails_the_build_naming_it():
    """The bite's 'done when', exactly: strip one field's rung and the pack no
    longer classifies — and the failure names the field, so the fix is where the
    omission is and not a hunt. This is I-11 at import, on a real schema."""
    for victim in custody.SCHEMA:
        wounded = copy.deepcopy(custody.SCHEMA)
        del wounded[victim]["rung"]
        with pytest.raises(Exception) as caught:
            classify_schema(wounded)
        assert victim in str(caught.value), (
            f"stripping {victim}'s rung must fail the build and name {victim}"
        )


def test_a_name_based_default_is_not_what_saved_this_pack():
    """The rungs are declared, not inferred. Proof: the *same* field names, with
    their declarations removed, all fail — so nothing here is keyed on the name
    'ssn' looking dangerous. classify_schema never guesses from a name."""
    for name in custody.SCHEMA:
        with pytest.raises(Exception):
            classify_schema({name: None})


# ── L2a-pack-contract: JURISDICTIONS and "derived" (decisions 1 and 3) ───────

def test_the_pack_default_jurisdiction_is_in_its_supported_tuple():
    """Decision 1: `JURISDICTION` is the default an instance starts under, and
    it must be a member of `JURISDICTIONS` — the household's order was entered
    in New Mexico and is being registered in Oregon, so both are supported and
    the default is the order's own forum."""
    assert custody.JURISDICTIONS == ("US-NM", "US-OR")
    assert custody.JURISDICTION == "US-NM"
    assert custody.JURISDICTION in custody.JURISDICTIONS


def test_every_l3_l4_custody_field_declares_its_derived_form_in_the_pack():
    """Decision 3: every field the gate can ever serve as a stand-in (`L3`,
    `L4`) carries a non-empty `"derived"` sentence in the pack itself — not in
    the CLI, not in the browser UI, both of which used to keep their own copy
    of this exact table (`cli._default_derived`, `server._derived`, both
    deleted by this bite) and read `derived_of(schema, field)` instead."""
    checked = 0
    for field, rung in custody.FIELDS.items():
        if rung in (Rung.L3, Rung.L4):
            sentence = custody.SCHEMA[field].get("derived")
            assert isinstance(sentence, str) and sentence.strip(), (
                f"{field} is {rung.value} and must carry a non-empty 'derived' "
                "sentence in the pack"
            )
            checked += 1
    assert checked == 7 + 6, (
        "expected custody's seven L3 + six L4 fields (L3-custody-relocation "
        "added custody_type/move_date/relocation_notice_date at L3 and "
        "child.name/child.dob/child.school at L4)"
    )


def test_derived_forms_match_the_engine_pack_where_the_field_exists():
    """The engine's own 0.3.0 custody pack already carries `"derived"` for
    `case_number`, `docket`, `opposing_party`, `parenting_time`, `child_name`,
    `diagnosis` and `notes`. Copying the sentence by hand invites the two packs
    to drift the instant one is edited and the other is not — so this compares
    them, field by field, rather than merely promising they match."""
    from homestead.packs import custody as engine_custody

    shared = sorted(set(custody.SCHEMA) & set(engine_custody.SCHEMA))
    assert len(shared) >= 7, "expected at least the seven shared L3/L4 fields"
    checked = 0
    for field in shared:
        ours = custody.SCHEMA[field].get("derived")
        theirs = engine_custody.SCHEMA[field].get("derived")
        if theirs is None:
            continue  # a field the engine never serves derived (e.g. an L1/L5)
        assert ours == theirs, (
            f"{field}'s derived form has drifted from the engine's own custody "
            f"pack: {ours!r} != {theirs!r}"
        )
        checked += 1
    assert checked >= 7, "expected all seven shared L3/L4 fields to be compared"


def test_every_why_names_a_step():
    """Step 5 of the classification procedure is that every rung is recorded
    *with* a reason, and the reason names which of steps 1-4 it answers — a
    `why` that never says 'step N' has not shown its work, and could be hiding
    a rung chosen by feel rather than by the procedure."""
    import re

    step = re.compile(r"\bstep \d\b")
    for field, spec in custody.SCHEMA.items():
        why = spec.get("why", "")
        assert step.search(why), f"{field}'s why never names a step: {why!r}"


# ── L3-custody-relocation (wave 3) ────────────────────────────────────────────

#: field → (rung, exact derived sentence) for every L3/L4 field this bite adds.
#: A dedicated table, not folded into the generic scans above, so this bite's
#: own exit criterion is pinned by name and does not silently ride on a
#: generic assertion whose wording could change for an unrelated reason.
_NEW_L3_L4_FIELDS = {
    "custody_type": (Rung.L3, "A custody arrangement type is on file"),
    "move_date": (Rung.L3, "A move date is on file"),
    "relocation_notice_date": (Rung.L3, "A relocation notice date is on file"),
    "child.name": (Rung.L4, "A child's name is on file"),
    "child.dob": (Rung.L4, "A child's date of birth is on file"),
    "child.school": (Rung.L4, "A school is on file"),
}

#: field → rung for the new L1/L2 fields — none of which carries (or needs) a
#: derived form.
_NEW_L1_L2_FIELDS = {
    "custody_order_date": Rung.L1,
    "uccjea_registration_date": Rung.L1,
    "registration_contest_deadline": Rung.L1,
    "mediation_date": Rung.L1,
    "new_residence_state": Rung.L2,
}


def test_the_relocation_l3_l4_fields_declare_their_rung_and_derived_form():
    """Every field this bite adds at L3/L4: the rung matches the plan
    exactly, the derived sentence matches exactly (not merely "is present"),
    and the sentence carries no digit — a schema-level stand-in is one
    sentence for every instance of the field (I-12's composition rule
    extended to text), so anything that varies with the value would be false
    for some records or would restate the value it exists to withhold."""
    for field, (rung, derived) in _NEW_L3_L4_FIELDS.items():
        assert custody.FIELDS[field] is rung, field
        assert custody.SCHEMA[field].get("derived") == derived, field
        assert not any(ch.isdigit() for ch in derived), (
            f"{field}'s derived form carries a digit: {derived!r}"
        )


def test_the_relocation_l1_l2_fields_declare_their_rung_and_no_derived_form():
    """L1/L2 fields render their own payload on `S1_LIST` (decision 3 only
    requires a stand-in for L3/L4), so none of these carries one — a `derived`
    key here would be dead text nothing ever substitutes."""
    for field, rung in _NEW_L1_L2_FIELDS.items():
        assert custody.FIELDS[field] is rung, field
        assert custody.SCHEMA[field].get("derived") is None, field


def test_every_new_field_is_in_the_pinned_rung_tables():
    """The two tables above account for every field `test_the_pack_spans_the
    _ladder_with_defensible_rungs`'s `expected` dict grew by relative to the
    pre-relocation pack — so a field added to one and not exercised here
    cannot happen silently."""
    pre_relocation = {
        "courthouse", "hearing_date", "jurisdiction", "case_number", "docket",
        "opposing_party", "parenting_time", "child_name", "diagnosis",
        "notes", "ssn",
    }
    added = set(custody.SCHEMA) - pre_relocation
    assert added == set(_NEW_L3_L4_FIELDS) | set(_NEW_L1_L2_FIELDS)


def test_repeatable_names_the_three_child_subfields():
    """Decision 2's `REPEATABLE`, held to the exact set — see the module
    docstring's "The relocation" section for why the three dotted field names
    are what is declared, rather than the bare word `"child"`: `cli._cmd_put`
    and the registry's own `unknown_repeatable` guard both check a member
    against the literal field string a `put` call names, and there is no bare
    `"child"` field for either to match."""
    assert custody.REPEATABLE == frozenset(
        {"child.name", "child.dob", "child.school"}
    )
    for field in custody.REPEATABLE:
        assert field in custody.FIELDS, field
        assert field.startswith("child."), field
        assert custody.FIELDS[field] is Rung.L4, field


def test_child_name_is_struck_through_never_deleted():
    """House style: struck through, never deleted. The old flat `child_name`
    field is documented as superseded in the module docstring (dated
    2026-09-11) but stays a real, classified field — `cli.py`'s
    `party_fields`, `server.py`'s intake form and the existing regression
    suite all still address it, and this bite does not touch any of those
    files (out of scope; see the docstring's own account of why)."""
    assert "child_name" in custody.SCHEMA
    assert custody.FIELDS["child_name"] is Rung.L4
    assert "~~`child_name`~~" in custody.__doc__
    assert "2026-09-11" in custody.__doc__


def test_child_name_and_child_dot_name_both_exist_until_l4_surfaces_retires_it():
    """The retirement of `child_name` is a *visible, tested* change, not a
    quiet one (audit, 2026-09-11).

    `child_name` is superseded by the repeatable `child.name` and struck
    through in the pack's prose, but it is still live: `cli.py`'s
    `party_fields`, `server.py`'s intake form and `app/demo.py` all address
    it. This test holds **both** on file at L4 for as long as that is true.
    The bite that retires the field is L4-surfaces (wave 4) — the bite that
    already rewrites every door naming it — and this assertion is what that
    bite will have to come here and change, deliberately, rather than
    discovering afterwards that a door went quiet.
    """
    assert custody.FIELDS["child_name"] is Rung.L4
    assert custody.FIELDS["child.name"] is Rung.L4
    assert custody.SCHEMA["child_name"]["derived"] == "A minor child is named in this matter"
    assert custody.SCHEMA["child.name"]["derived"] == "A child's name is on file"
    # `child_name` is NOT repeatable: it is the singular field being retired,
    # so it keeps taking no `--sub` right up until it goes.
    assert "child_name" not in custody.REPEATABLE
    assert "child.name" in custody.REPEATABLE

    # the strike-through names the bite that retires it, and is dated.
    why = custody.SCHEMA["child_name"]["why"]
    assert "~~Superseded 2026-09-11 by the repeatable `child.name`~~" in why
    assert "L4-surfaces" in why
