"""`homestead_law.packs.workers_comp` — an active New Mexico WCA claim (wave 3,
decision 7). Same shape as `tests/test_packs.py` (the custody pack's own
suite): schema contract, the ladder, the derived-form rule — plus this pack's
own additions: the three dotted `ime.*` repeatable fields, the `L4` length cap
(`validate_value`, whose wiring into the doors is a pending xfail here, not an
assertion that the doors stay unwired), and `TEMPLATES` — empty, because every
candidate NM rule anchors above `L1`, with the shape check that holds anything
added later to that rule.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from homestead.keep.rungs import Classified, Disposition, Rung, Surface, serve
from homestead_law import instances
from homestead_law.packs import workers_comp
from homestead_law.registry import all_matters, matter
from homestead_law.store import Sidecar

MATTER = workers_comp.MATTER  # "workers_comp"


# ── the pack classifies at import, and registers ─────────────────────────────

def test_the_pack_classifies_at_import():
    assert isinstance(workers_comp.FIELDS, dict)
    assert workers_comp.FIELDS
    assert all(isinstance(r, Rung) for r in workers_comp.FIELDS.values())
    assert set(workers_comp.FIELDS) == set(workers_comp.SCHEMA)


def test_the_pack_is_registered():
    assert MATTER in all_matters()
    entry = matter(MATTER)
    assert entry.pack is workers_comp
    assert entry.fields is workers_comp.FIELDS
    assert entry.jurisdiction == "US-NM"
    assert entry.jurisdictions == ("US-NM",)


def test_jurisdictions_is_a_single_nm_member():
    """Decision: the claim stays an NM claim after the move — treatment moves,
    the forum does not (unlike custody's US-NM -> US-OR)."""
    assert workers_comp.JURISDICTIONS == ("US-NM",)
    assert workers_comp.JURISDICTION == "US-NM"
    assert workers_comp.JURISDICTION in workers_comp.JURISDICTIONS


# ── the ladder, field by field (item 1's list) ────────────────────────────────

EXPECTED = {
    "jurisdiction": Rung.L1,
    "wca_case_number": Rung.L3,
    "claim_number": Rung.L3,
    "employer": Rung.L3,
    "insurer": Rung.L3,
    "adjuster": Rung.L3,
    "notice_of_accident_date": Rung.L3,
    "hcp_change_objection_deadline": Rung.L3,
    "mediation_date": Rung.L3,
    "hearing_date": Rung.L3,
    "complaint_date": Rung.L3,
    "date_of_injury": Rung.L4,
    "body_part": Rung.L4,
    "diagnosis": Rung.L4,
    "impairment_rating": Rung.L4,
    "mmi_date": Rung.L4,
    "treating_physician": Rung.L4,
    "hcp_selection_date": Rung.L4,
    "ime.date": Rung.L4,
    "ime.examiner": Rung.L4,
    "ime.note": Rung.L4,
    "aww": Rung.L4,
    "benefit_rate": Rung.L4,
    "tt_benefit_start": Rung.L4,
    "oos_provider_affidavit_date": Rung.L4,
    "notes": Rung.L4,
    "ssn": Rung.L5,
}


def test_the_pack_spans_the_ladder_with_the_declared_rungs():
    assert workers_comp.FIELDS == EXPECTED


@pytest.mark.parametrize("field,rung", sorted(EXPECTED.items()))
def test_schema_contract_per_field(field, rung):
    """Every field: matter, jurisdiction, why recorded — step 5 of the
    classification procedure, the same contract custody's pack holds."""
    spec = workers_comp.SCHEMA[field]
    assert spec["rung"] is rung
    assert spec.get("matter") == MATTER
    assert spec.get("jurisdiction") == "US-NM"
    assert spec.get("why"), f"{field} declares a rung with no recorded reason"


def test_the_dangerous_rungs_are_where_they_must_be():
    assert workers_comp.FIELDS["ssn"] is Rung.L5, "an SSN is L5 — L5 has no override"
    assert workers_comp.FIELDS["date_of_injury"] is Rung.L4
    assert workers_comp.FIELDS["diagnosis"] is Rung.L4


def test_only_the_jurisdiction_is_l1_and_no_medical_date_sits_beside_it():
    """The audit's ruling on `hcp_selection_date` (2026-09-11), as a test.

    A rung answers the harm of disclosing the value, never what a deadline
    template needs for an anchor. `L1` means *public in this matter's forum*,
    and this pack has already ruled its forum does not post — `wca_case_number`
    is `L3` for exactly that reason, and so are `hearing_date` and
    `mediation_date`. A date that says a health care provider was chosen for
    this claimant cannot be more public than the hearing it schedules, so no
    provider- or treatment-dated field may appear at `L1` here. The field that
    started this — `hcp_selection_date`, shipped `L1` so the 60-day window
    could be computed — is `L4`, and the template is the thing that went.
    """
    assert [f for f, r in workers_comp.FIELDS.items() if r is Rung.L1] == ["jurisdiction"]
    assert workers_comp.FIELDS["hcp_selection_date"] is Rung.L4
    assert "hcp_change_notice_date" not in workers_comp.FIELDS
    for field in ("hcp_selection_date", "mmi_date", "tt_benefit_start",
                  "oos_provider_affidavit_date", "ime.date"):
        assert workers_comp.FIELDS[field] is Rung.L4, field


def test_deleting_a_fields_rung_fails_the_build_naming_it():
    import copy

    from homestead.keep.rungs import classify_schema

    for victim in workers_comp.SCHEMA:
        wounded = copy.deepcopy(workers_comp.SCHEMA)
        del wounded[victim]["rung"]
        with pytest.raises(Exception) as caught:
            classify_schema(wounded)
        assert victim in str(caught.value)


# ── REPEATABLE (decision 2) ───────────────────────────────────────────────────

_IME_FIELDS = ("ime.date", "ime.examiner", "ime.note")


def test_repeatable_names_the_three_dotted_ime_fields():
    """One convention across the law packs (audit, 2026-09-11).

    `homestead_law.packs.custody` declares `child.name`/`child.dob`/
    `child.school` — dotted sub-fields, each in `SCHEMA` and each in
    `REPEATABLE` — because that is what the write door can drive: `_cmd_put`
    holds the *typed* field string against `mt.repeatable`, and
    `registry._validate` holds every `REPEATABLE` member against `FIELDS`. A
    bare `"ime"` needs a bare `"ime"` field, which is one free-text blob per
    exam beside `notes`. This pack follows custody.
    """
    assert workers_comp.REPEATABLE == frozenset(_IME_FIELDS)
    assert matter(MATTER).repeatable is workers_comp.REPEATABLE
    assert "ime" not in workers_comp.FIELDS
    for field in _IME_FIELDS:
        assert field in workers_comp.FIELDS


def test_every_repeatable_field_is_declared(monkeypatch):
    """The registry's own `unknown_repeatable` guard, run against this pack —
    and planted: a `REPEATABLE` member with no field behind it is the
    hand-kept phantom I-23 forbids."""
    from homestead_law import registry as registry_mod

    registry_mod._validate(registry_mod.REGISTRY, registry_mod._discover_packs())

    monkeypatch.setattr(workers_comp, "REPEATABLE", frozenset({"ime"}), raising=True)
    with pytest.raises(Exception) as caught:
        registry_mod._validate(registry_mod.REGISTRY, registry_mod._discover_packs())
    assert "ime" in str(caught.value)


@pytest.mark.parametrize("field", _IME_FIELDS)
def test_an_ime_sub_record_round_trips_and_reads_back_derived(field, tmp_path, monkeypatch):
    """`put workers_comp ime.date 2026-10-05 --id primary --sub 2026-10`, and
    the same `--sub` for the examiner and the note — three records, one exam,
    no field holding all three. Exercised against the store the way
    `tests/test_jurisdiction.py` and `tests/test_queue.py` exercise a write,
    without the Nestor-gated CLI."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    item_id = instances.item_id("primary", "2026-10")
    assert item_id == "primary.2026-10"
    assert instances.split_item_id(item_id) == ("primary", "2026-10")

    values = {
        "ime.date": "2026-10-05",
        "ime.examiner": "Dr. R. Chen",
        "ime.note": "report received; no permanent restrictions",
    }
    derived = workers_comp.SCHEMA[field]["derived"]
    store.put(
        MATTER, field, item_id,
        Classified(workers_comp.FIELDS[field], values[field], derived),
    )

    served = serve(store.get(MATTER, field, item_id), Surface.S1_LIST)
    assert served.disposition is Disposition.DERIVE
    assert served.value == derived
    assert values[field] not in served.value  # the payload never reaches S1_LIST
    assert "Chen" not in served.value


def test_a_second_exam_does_not_overwrite_the_first(tmp_path, monkeypatch):
    """The reason for one record per `--sub` rather than one `ime` field: two
    exams coexist, addressed by their own sub-ids."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    derived = workers_comp.SCHEMA["ime.date"]["derived"]
    for sub, value in (("2026-10", "2026-10-05"), ("2027-03", "2027-03-11")):
        store.put(
            MATTER, "ime.date", instances.item_id("primary", sub),
            Classified(Rung.L4, value, derived),
        )
    first = store.get(MATTER, "ime.date", "primary.2026-10")
    second = store.get(MATTER, "ime.date", "primary.2027-03")
    assert first is not None and second is not None
    assert serve(first, Surface.S1_LIST).value == derived
    assert serve(second, Surface.S1_LIST).value == derived


# ── derived forms: no digit, and date_of_injury carries no year at all ───────

def test_every_l3_l4_field_declares_a_non_empty_derived_form():
    checked = 0
    for field, rung in workers_comp.FIELDS.items():
        if rung in (Rung.L3, Rung.L4):
            sentence = workers_comp.SCHEMA[field].get("derived")
            assert isinstance(sentence, str) and sentence.strip(), field
            checked += 1
    l3 = sum(1 for r in EXPECTED.values() if r is Rung.L3)
    l4 = sum(1 for r in EXPECTED.values() if r is Rung.L4)
    assert checked == l3 + l4


def test_no_derived_form_carries_a_digit():
    for field in workers_comp.SCHEMA:
        sentence = workers_comp.SCHEMA[field].get("derived")
        if sentence is None:
            continue
        assert not any(ch.isdigit() for ch in sentence), f"{field}: {sentence!r}"


_MONTHS = (
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
)


_SEASONS = ("spring", "summer", "autumn", "fall", "winter")


def test_date_of_injurys_derived_form_carries_no_year_and_no_month_name():
    sentence = workers_comp.SCHEMA["date_of_injury"]["derived"]
    assert not any(ch.isdigit() for ch in sentence)
    lowered = sentence.lower()
    assert not any(month in lowered for month in _MONTHS)
    assert sentence == "A date of injury is on file"


def test_no_derived_form_anywhere_carries_a_month_or_a_season():
    """Not only `date_of_injury`: this pack is mostly dates, and a derived
    form that narrowed any of them to a month or a season would put the
    payload back on the surface it was withheld from."""
    for field, spec in workers_comp.SCHEMA.items():
        sentence = spec.get("derived")
        if sentence is None:
            continue
        lowered = sentence.lower()
        for word in _MONTHS + _SEASONS:
            assert word not in lowered, f"{field}: {sentence!r} ({word})"


def test_no_derived_form_asserts_a_state_or_a_magnitude():
    """Every derived sentence says a thing is *on file* or *is named* — never
    that benefits are being paid, that a rating is high, or what any value
    is. The rule the rungs procedure states as "neither the value, nor a
    name, nor a magnitude".

    A derived form may still *name its own field's subject* — "a medical
    diagnosis", "a temporary total benefit start date" — the way custody's
    already do; that is the field name, which the surface knows anyway, not
    the payload. What it may not do is assert a state ("benefits are being
    paid") or a size."""
    for field, spec in workers_comp.SCHEMA.items():
        sentence = spec.get("derived")
        if sentence is None:
            continue
        assert ("is on file" in sentence or "is named" in sentence), (
            f"{field}: {sentence!r}"
        )
        lowered = sentence.lower()
        for banned in ("paid", "receiving", "owed", "high", "low", "severe",
                       "percent", "%", "$", "weekly benefits", "per week",
                       "approved", "denied", "pending", "open", "closed"):
            assert banned not in lowered, f"{field}: {sentence!r} ({banned})"


# ── validate_value — the L4 length cap (item 2) ───────────────────────────────

def test_validate_value_accepts_200_chars_on_an_l4_field():
    workers_comp.validate_value("diagnosis", "x" * workers_comp.MAX_L4_CHARS)


def test_validate_value_ignores_non_l4_and_unknown_fields_regardless_of_length():
    long_value = "x" * 5000
    for field in ("wca_case_number", "jurisdiction", "ssn", "not_a_real_field"):
        workers_comp.validate_value(field, long_value)  # L3, L1, L5, unknown


def test_validate_value_refuses_every_l4_field_over_the_cap():
    for field, rung in workers_comp.FIELDS.items():
        if rung is not Rung.L4:
            continue
        with pytest.raises(workers_comp.MedicalNarrativeTooLong):
            workers_comp.validate_value(field, "x" * (workers_comp.MAX_L4_CHARS + 1))


def test_validate_value_refuses_201_chars_naming_the_field_never_echoing():
    """The whole contract of the message, in one place: it names the field, it
    names where the content belongs, it gives the cap — and it repeats no part
    of what was typed (I-15: a reference, never content)."""
    secret = "L5 SPINAL STENOSIS AT C5-C6 PER DR CHEN"
    value = secret + "x" * (workers_comp.MAX_L4_CHARS + 1 - len(secret))

    assert len(value) == workers_comp.MAX_L4_CHARS + 1
    with pytest.raises(workers_comp.MedicalNarrativeTooLong) as exc:
        workers_comp.validate_value("ime.note", value)

    message = str(exc.value)
    assert "ime.note" in message
    assert "homestead-health" in message
    assert str(workers_comp.MAX_L4_CHARS) in message
    for fragment in (secret, "SPINAL", "STENOSIS", "C5-C6", "Chen"):
        assert fragment not in message
    assert exc.value.field == "ime.note"
    assert isinstance(exc.value, ValueError)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "L4-surfaces (wave 4) is the bite that calls validate_value from "
        "cli._cmd_put and server /api/store. Until it lands the doors store an "
        "over-long L4 value unchecked; when it lands this XPASSes, which under "
        "strict xfail fails the suite by name — the signal to delete the mark "
        "and keep the test, the same promotion mechanic "
        "homestead's tests/test_invariants_pending.py uses."
    ),
)
def test_the_doors_call_validate_value():
    """The contract this pack is waiting on, written as a claim rather than as
    an assertion that the gap stays open.

    ~~`assert "validate_value" not in cli_source`~~ was the shipped shape and
    is struck (audit, 2026-09-11): a test that goes red the day a later bite
    does the right thing is a landmine for that bite, and it asserts the
    absence of a feature instead of the presence of one.
    """
    from homestead_law import cli, server

    for module in (cli, server):
        assert "validate_value" in Path(module.__file__).read_text("utf-8"), module.__name__


# ── ssn never crosses S1_LIST or S2 ──────────────────────────────────────────

def test_ssn_crosses_nothing_at_all():
    """Every surface the engine defines, not a chosen two — "L5 has no
    override anywhere" is a claim about the whole enum, and a new member
    should make this test speak rather than stay silent (I-13, step 4)."""
    assert workers_comp.FIELDS["ssn"] is Rung.L5
    record = Classified(Rung.L5, "123-45-6789")
    assert len(list(Surface)) >= 5
    for surface in Surface:
        served = serve(record, surface)
        assert served.disposition is Disposition.DENY, surface
        assert served.value is None, surface


def test_no_l4_field_renders_its_payload_on_any_surface_below_s1_detail():
    """Decision 7's boundary, as behaviour: every medical-adjacent field in
    this pack derives or is denied wherever the operator is not the reader —
    the pack holds a date or a reference, and even that never leaves S1."""
    payload = "PAYLOAD-THAT-MUST-NOT-CROSS"
    for field, rung in workers_comp.FIELDS.items():
        if rung is not Rung.L4:
            continue
        record = Classified(rung, payload, workers_comp.SCHEMA[field]["derived"])
        for surface in (Surface.S1_LIST, Surface.S2_PROMPT, Surface.S3_AGENT,
                        Surface.S4_EGRESS):
            served = serve(record, surface)
            assert served.value != payload, (field, surface)
            assert served.disposition is not Disposition.RENDER, (field, surface)
            assert served.disposition in (Disposition.DERIVE, Disposition.DENY)


def test_every_l4_medical_why_names_health_as_the_home_of_the_content():
    """Decision 7 in prose, held to: a field that touches the claimant's
    medical facts says, in its own `why`, that the narrative lives in
    homestead-health — so nobody adding a field here has to rediscover it."""
    medical = (
        "date_of_injury", "body_part", "diagnosis", "impairment_rating",
        "mmi_date", "treating_physician", "hcp_selection_date",
        "ime.date", "ime.examiner", "ime.note",
        "oos_provider_affidavit_date", "notes",
    )
    for field in medical:
        why = workers_comp.SCHEMA[field]["why"]
        assert workers_comp.FIELDS[field] is Rung.L4, field
        assert "homestead-health" in why or "MAX_L4_CHARS" in why, field


def test_notes_and_the_exam_note_are_the_only_free_text_fields():
    """The 200-char cap is the guard on free text (once a door calls it), so
    the set of free-text fields is a thing this pack states rather than
    lets drift. Everything else here holds a date, a name or a number."""
    free_text = {"notes", "ime.note"}
    assert free_text <= set(workers_comp.FIELDS)
    for field in free_text:
        assert workers_comp.FIELDS[field] is Rung.L4
        with pytest.raises(workers_comp.MedicalNarrativeTooLong):
            workers_comp.validate_value(field, "x" * (workers_comp.MAX_L4_CHARS + 1))


# ── TEMPLATES (item 3) — data only ────────────────────────────────────────────

def test_templates_does_not_import_rules():
    """TEMPLATES is data the parallel `L3-deadline-templates` bite reads; this
    pack must not import that sibling's module (the two run side by side).
    An AST scan, not a text search, because the module's own docstring names
    `homestead_law.rules` in prose to explain exactly this."""
    import ast

    source = Path(workers_comp.__file__).read_text("utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("homestead_law.rules"), node.module
            assert node.module != "homestead_law.rules"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("homestead_law.rules"), alias.name


def test_this_pack_computes_no_deadline_because_every_anchor_is_above_l1():
    """The audit's ruling (2026-09-11), as a test.

    All three NM rules this matter carries — the 60-day HCP-change window
    (§ 52-1-49(B)-(C)), the 3-day objection window, the 15-day notice of
    accident (§ 52-1-29) — anchor on a field declared `L4`. `compute()` reads
    an anchor through the gate on `S1_LIST`, where an `L4` value renders as
    its derived form, so no date reaches the arithmetic; the template cannot
    exist, and the rung does not move to make room for one. Each deadline is
    entered instead.
    """
    assert workers_comp.TEMPLATES == ()
    for anchor in ("hcp_selection_date", "date_of_injury"):
        assert workers_comp.FIELDS[anchor] is Rung.L4
    # ...and the fields the household enters those dates into exist.
    for field in ("hcp_change_objection_deadline", "notice_of_accident_date", "notes"):
        assert field in workers_comp.FIELDS


def test_the_citations_survived_the_templates_that_carried_them():
    """Dropping a computed template must not drop the statute it cited — the
    reference is the part the household keeps."""
    assert "52-1-49" in workers_comp.SCHEMA["hcp_selection_date"]["why"]
    assert "52-1-29" in workers_comp.SCHEMA["notice_of_accident_date"]["why"]
    assert "52-4-1" in workers_comp.SCHEMA["oos_provider_affidavit_date"]["why"]


def test_an_empty_templates_still_passes_its_own_shape_check():
    """Already run once at import; re-run explicitly so the suite keeps
    exercising it (registry.py's own `_validate` pattern)."""
    workers_comp._validate_templates(
        workers_comp.TEMPLATES, workers_comp.SCHEMA, workers_comp.FIELDS,
        workers_comp.JURISDICTIONS,
    )


def test_the_template_name_pattern_has_not_drifted_from_instances():
    """`_TEMPLATE_NAME` is `instances.ID_PATTERN` copied, so a pack stays a
    leaf that imports only the engine's `rungs`. Copied, therefore checked."""
    assert workers_comp._TEMPLATE_NAME.pattern == instances.ID_PATTERN.pattern


# ── the shape check fires on planted violations ───────────────────────────────

def _good_template() -> dict:
    """A synthetic well-shaped entry — this pack declares none of its own (see
    `test_this_pack_computes_no_deadline_because_every_anchor_is_above_l1`), so
    the planted violations below are mutations of a template built here. Its
    anchor is the one `L1` field the pack has, which is what the shape rule
    requires of any anchor; nothing stores or computes from this dict."""
    return {
        "name": "a-synthetic-template",
        "anchor": "jurisdiction",
        "days": 60,
        "direction": "forward",
        "rule": "calendar_days",
        "mail": False,
        "jurisdiction": "US-NM",
        "source": "a citation would go here",
        "status": "UNCERTAIN",
        "note": "a note would go here",
    }


def test_the_synthetic_template_is_actually_well_shaped():
    """Otherwise every planted test below could be passing for the wrong
    reason — a fixture that never validates proves nothing about the mutation
    that broke it."""
    _check([_good_template()])


def _check(templates):
    workers_comp._validate_templates(
        tuple(templates), workers_comp.SCHEMA, workers_comp.FIELDS,
        workers_comp.JURISDICTIONS,
    )


@pytest.mark.parametrize(
    "key,bad_value,needle",
    [
        ("extra_field", "surprise", "extra_field"),   # unexpected key (+ missing below)
        ("anchor", "not_a_real_field", "not_a_real_field"),
        ("direction", "sideways", None),
        ("rule", "moon_days", None),
        ("status", "PROBABLY", None),
        ("jurisdiction", "US-OR", None),
        ("mail", "no", None),
        ("days", 0, None),
        ("days", -3, None),
        ("days", "60", None),
        ("days", True, None),
        ("source", "   ", None),
        ("note", "   ", None),
        ("name", "   ", None),
        ("name", "has_an_underscore", "underscore"),
        ("name", "Has-A-Capital", "_TEMPLATE_NAME_MESSAGE"),
        ("name", "has.a.dot", "_TEMPLATE_NAME_MESSAGE"),
        ("name", "-starts-with-a-hyphen", "_TEMPLATE_NAME_MESSAGE"),
        ("name", "x" * 41, "_TEMPLATE_NAME_MESSAGE"),
    ],
)
def test_shape_check_fires_on_each_kind_of_planted_violation(key, bad_value, needle):
    bad = _good_template()
    bad[key] = bad_value
    with pytest.raises(workers_comp.TemplateShapeError) as exc:
        _check([bad])
    if needle == "_TEMPLATE_NAME_MESSAGE":
        assert "repeatable sub-id" in str(exc.value)
    elif needle:
        assert needle in str(exc.value)


def test_shape_check_fires_on_a_missing_key():
    bad = _good_template()
    del bad["source"]
    with pytest.raises(workers_comp.TemplateShapeError) as exc:
        _check([bad])
    assert "source" in str(exc.value)


@pytest.mark.parametrize(
    "anchor", ["date_of_injury", "hcp_selection_date", "wca_case_number", "ssn"]
)
def test_shape_check_fires_on_an_anchor_above_l1(anchor):
    """The rule that decided this bite, planted at every rung above `L1`:
    a computed template cannot read an anchor a surface might withhold, so the
    build fails rather than the rung moving down to suit the template."""
    bad = _good_template()
    bad["anchor"] = anchor
    with pytest.raises(workers_comp.TemplateShapeError) as exc:
        _check([bad])
    assert anchor in str(exc.value)
    assert "L1" in str(exc.value)


def test_shape_check_accepts_a_none_jurisdiction():
    good = _good_template()
    good["jurisdiction"] = None
    _check([good])


def test_shape_check_fires_on_a_non_dict_entry():
    with pytest.raises(workers_comp.TemplateShapeError):
        _check(["not-a-dict"])


# ── decision 8 / I-44: this pack tracks, it never advises ───────────────────

_ADVICE = (
    "you should", "you must", "you need to", "file by", "we recommend",
    "which chapter", "be sure to", "make sure you", "don't forget",
)


def test_no_why_or_derived_form_tells_the_household_what_to_do():
    """The README says this pack's own text is held against advice language;
    this is that check. A pack records what is on file and cites the statute
    behind a date — it never instructs (decision 8's posture, whose
    package-wide AST guard is a sibling bite's)."""
    checked = 0
    for field, spec in workers_comp.SCHEMA.items():
        for key in ("why", "derived"):
            text = spec.get(key)
            if text is None:
                continue
            lowered = text.lower()
            for phrase in _ADVICE:
                assert phrase not in lowered, f"{field}.{key}: {phrase!r}"
            checked += 1
    assert checked >= len(workers_comp.SCHEMA)


def test_the_advice_scan_fires_on_a_planted_sentence():
    """A scan that has never fired has not been shown to check anything."""
    planted = dict(workers_comp.SCHEMA["notes"])
    planted["why"] = "you should file by the deadline"
    lowered = planted["why"].lower()
    assert any(phrase in lowered for phrase in _ADVICE)


# ── I-23: the registry scan stays green with this pack on disk ──────────────

def test_registering_this_pack_did_not_break_the_i23_scan():
    from homestead_law import registry as registry_mod

    assert set(all_matters()) == set(registry_mod.REGISTRY) == set(registry_mod._discover_packs())
    registry_mod._validate(registry_mod.REGISTRY, registry_mod._discover_packs())
