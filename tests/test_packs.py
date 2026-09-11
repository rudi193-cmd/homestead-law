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
    assert checked == 4 + 3, "expected custody's four L3 + three L4 fields"


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
